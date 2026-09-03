using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Auth;
using DancePlatform.API.Models;
using DancePlatform.API.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace DancePlatform.Tests;

/// <summary>
/// The account-recovery flow, against SQLite in-memory. What matters here isn't that a happy
/// path works — it's the properties that make the flow safe to expose publicly: the mailed
/// token is never stored, a spent link can't be replayed, and a reset actually retires the
/// sessions of whoever knew the old password.
/// </summary>
public class AuthServiceTests : IDisposable
{
    private readonly SqliteConnection _conn;
    private readonly DbContextOptions<AppDbContext> _options;
    private readonly RecordingEmailSender _email = new();
    private readonly IMemoryCache _cache = new MemoryCache(new MemoryCacheOptions());

    public AuthServiceTests()
    {
        _conn = new SqliteConnection("DataSource=:memory:");
        _conn.Open();
        _options = new DbContextOptionsBuilder<AppDbContext>().UseSqlite(_conn).Options;

        using var ctx = new AppDbContext(_options);
        ctx.Database.EnsureCreated();
        ctx.Users.Add(new User
        {
            Id = 1,
            Username = "Justas",
            Email = "dancer@example.com",
            PasswordHash = BCrypt.Net.BCrypt.HashPassword("old-password"),
            Name = "Justas",
            Nickname = ""
        });
        ctx.SaveChanges();
    }

    private AppDbContext NewCtx() => new(_options);

    private AuthService NewService(AppDbContext ctx)
    {
        var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["Jwt:Key"] = "test-signing-key-long-enough-for-hmac-sha256",
            ["Jwt:Issuer"] = "DancePlatform",
            ["Jwt:Audience"] = "DancePlatformUsers",
            ["App:UiUrl"] = "https://dance.takelord.com"
        }).Build();

        return new AuthService(ctx, new TokenService(config), _email, config, _cache,
            NullLogger<AuthService>.Instance);
    }

    /// <summary>Pulls the token out of the mail body the way a user clicking the link would.</summary>
    private static string TokenFromLink(string body)
    {
        var marker = "reset-password?token=";
        var start = body.IndexOf(marker, StringComparison.Ordinal) + marker.Length;
        var end = body.IndexOf('\n', start);
        return Uri.UnescapeDataString(body[start..end].Trim());
    }

    [Fact]
    public async Task ResetLinkIsMailedAndTheTokenItselfIsNeverStored()
    {
        await using (var ctx = NewCtx())
            await NewService(ctx).RequestPasswordResetAsync("DANCER@example.com");

        // Case-insensitive lookup: a person types their address however they type it.
        Assert.Single(_email.Sent);
        var token = TokenFromLink(_email.Sent[0].Body);
        Assert.NotEmpty(token);

        await using var check = NewCtx();
        var stored = await check.PasswordResetTokens.SingleAsync();
        // The row holds a hash. Anyone reading the database — or a backup pulled to a laptop —
        // learns nothing they can spend.
        Assert.NotEqual(token, stored.TokenHash);
        Assert.DoesNotContain(token, stored.TokenHash, StringComparison.Ordinal);
    }

    [Fact]
    public async Task AnUnknownAddressIsSilentAndMailsNobody()
    {
        await using (var ctx = NewCtx())
            await NewService(ctx).RequestPasswordResetAsync("nobody@example.com");

        Assert.Empty(_email.Sent);
        await using var check = NewCtx();
        Assert.Empty(await check.PasswordResetTokens.ToListAsync());
    }

    [Fact]
    public async Task TheLinkSetsANewPasswordAndRetiresTheOldSessions()
    {
        await using (var ctx = NewCtx())
            await NewService(ctx).RequestPasswordResetAsync("dancer@example.com");
        var token = TokenFromLink(_email.Sent[0].Body);

        await using (var ctx = NewCtx())
        {
            var response = await NewService(ctx).ResetPasswordAsync(
                new ResetPasswordRequest { Token = token, NewPassword = "a-brand-new-password" });
            Assert.NotNull(response);
        }

        await using (var ctx = NewCtx())
        {
            var service = NewService(ctx);
            Assert.Null(await service.LoginAsync(
                new LoginRequest { Username = "Justas", Password = "old-password" }));
            Assert.NotNull(await service.LoginAsync(
                new LoginRequest { Username = "Justas", Password = "a-brand-new-password" }));
        }

        await using var check = NewCtx();
        // The cutoff is what signs out whoever knew the old password; a reset that only changed
        // the hash would leave them holding a valid token for the rest of its 30 days.
        Assert.NotNull((await check.Users.SingleAsync()).TokensValidFrom);
    }

    [Fact]
    public async Task ASpentLinkCannotBeUsedTwice()
    {
        await using (var ctx = NewCtx())
            await NewService(ctx).RequestPasswordResetAsync("dancer@example.com");
        var token = TokenFromLink(_email.Sent[0].Body);

        await using (var ctx = NewCtx())
            await NewService(ctx).ResetPasswordAsync(
                new ResetPasswordRequest { Token = token, NewPassword = "first-new-password" });

        await using (var ctx = NewCtx())
        {
            var replay = await NewService(ctx).ResetPasswordAsync(
                new ResetPasswordRequest { Token = token, NewPassword = "attacker-password" });
            Assert.Null(replay);
        }

        await using var ctx2 = NewCtx();
        Assert.NotNull(await NewService(ctx2).LoginAsync(
            new LoginRequest { Username = "Justas", Password = "first-new-password" }));
    }

    [Fact]
    public async Task AskingAgainKillsTheLinkAlreadyInFlight()
    {
        await using (var ctx = NewCtx())
            await NewService(ctx).RequestPasswordResetAsync("dancer@example.com");
        var first = TokenFromLink(_email.Sent[0].Body);

        await using (var ctx = NewCtx())
            await NewService(ctx).RequestPasswordResetAsync("dancer@example.com");
        var second = TokenFromLink(_email.Sent[1].Body);

        await using (var ctx = NewCtx())
        {
            // The reason to ask twice is often "I think someone saw the first mail".
            Assert.Null(await NewService(ctx).ResetPasswordAsync(
                new ResetPasswordRequest { Token = first, NewPassword = "should-not-apply" }));
        }

        await using (var ctx = NewCtx())
            Assert.NotNull(await NewService(ctx).ResetPasswordAsync(
                new ResetPasswordRequest { Token = second, NewPassword = "the-real-new-password" }));
    }

    [Fact]
    public async Task AnExpiredLinkIsRefused()
    {
        await using (var ctx = NewCtx())
            await NewService(ctx).RequestPasswordResetAsync("dancer@example.com");
        var token = TokenFromLink(_email.Sent[0].Body);

        await using (var ctx = NewCtx())
        {
            var row = await ctx.PasswordResetTokens.SingleAsync();
            row.ExpiresAt = DateTime.UtcNow.AddMinutes(-1);
            await ctx.SaveChangesAsync();
        }

        await using var check = NewCtx();
        Assert.Null(await NewService(check).ResetPasswordAsync(
            new ResetPasswordRequest { Token = token, NewPassword = "too-late" }));
    }

    [Fact]
    public async Task RegistrationRequiresAnAddressNobodyElseHas()
    {
        await using var ctx = NewCtx();
        var (result, _) = await NewService(ctx).RegisterAsync(new RegisterRequest
        {
            Username = "someone-new",
            Email = "DANCER@EXAMPLE.COM",
            Password = "password123",
            Name = "Someone"
        });

        // Same address in different casing is the same person — the reset flow could not choose
        // between two accounts sharing one mailbox.
        Assert.Equal(RegisterResult.EmailTaken, result);
    }

    [Fact]
    public async Task ChangingThePasswordRequiresTheCurrentOneAndRetiresOldTokens()
    {
        await using (var ctx = NewCtx())
        {
            var (wrong, _) = await NewService(ctx).ChangePasswordAsync(1,
                new ChangePasswordRequest { CurrentPassword = "not-it", NewPassword = "irrelevant" });
            Assert.Equal(PasswordChangeResult.WrongCurrentPassword, wrong);
        }

        await using (var ctx = NewCtx())
        {
            var (ok, response) = await NewService(ctx).ChangePasswordAsync(1,
                new ChangePasswordRequest { CurrentPassword = "old-password", NewPassword = "chosen-in-profile" });
            Assert.Equal(PasswordChangeResult.Ok, ok);
            // A fresh token comes back, because the one the caller asked with was just retired.
            Assert.NotNull(response);
            Assert.NotEmpty(response!.Token);
        }

        await using var check = NewCtx();
        Assert.NotNull(await NewService(check).LoginAsync(
            new LoginRequest { Username = "Justas", Password = "chosen-in-profile" }));
    }

    public void Dispose()
    {
        _conn.Dispose();
        GC.SuppressFinalize(this);
    }

    private sealed class RecordingEmailSender : IEmailSender
    {
        public List<(string To, string Subject, string Body)> Sent { get; } = new();
        public bool IsConfigured => true;

        public Task<bool> SendAsync(string to, string subject, string body, CancellationToken ct = default)
        {
            Sent.Add((to, subject, body));
            return Task.FromResult(true);
        }
    }
}
