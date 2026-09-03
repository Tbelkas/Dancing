using System.Security.Claims;
using System.Text;
using DancePlatform.API;
using DancePlatform.API.Data;
using DancePlatform.API.Services;
using DancePlatform.API.Services.ExternalAuth;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.AspNetCore.ResponseCompression;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddAppRateLimiting();
// Apache proxies from localhost, so RemoteIpAddress is 127.0.0.1 on every request until the
// forwarded header is honoured — and every rate-limit partition would be the same bucket.
// Only the loopback proxy is trusted (the defaults), so a client can't forge its own address.
builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
});
// Apache proxies to Kestrel over plain HTTP and passes upstream Content-Encoding through,
// so compressing here is what the browser ends up receiving.
builder.Services.AddResponseCompression(options =>
{
    options.EnableForHttps = true;
    options.Providers.Add<BrotliCompressionProvider>();
    options.Providers.Add<GzipCompressionProvider>();
});
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.AddProblemDetails();
// Backs the short-lived catalog-size cache in DanceService (see the "dances:grandTotal" key) so
// the "N of M dances" figure isn't a full COUNT(*) on every keystroke.
builder.Services.AddMemoryCache();

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("Default")));

builder.Services.AddSingleton<ITokenService, TokenService>();
// Singleton: the failed-attempt counters have to outlive the request that incremented them.
builder.Services.AddSingleton<ILoginThrottle, LoginThrottle>();
builder.Services.AddScoped<IAuthService, AuthService>();
builder.Services.AddScoped<IUserTokenGuard, UserTokenGuard>();
builder.Services.AddSingleton<IEmailSender, SmtpEmailSender>();
builder.Services.AddScoped<IDanceService, DanceService>();
builder.Services.AddScoped<IStyleService, StyleService>();
builder.Services.AddScoped<IMusicalStyleService, MusicalStyleService>();
builder.Services.AddScoped<IVideoService, VideoService>();
builder.Services.AddScoped<IUserVideoLoopService, UserVideoLoopService>();
builder.Services.AddScoped<IVideoNoteService, VideoNoteService>();
builder.Services.AddScoped<IChoreoService, ChoreoService>();
builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddScoped<IPracticeService, PracticeService>();
builder.Services.AddScoped<IInstructorService, InstructorService>();
builder.Services.AddScoped<IRoadmapService, RoadmapService>();
builder.Services.AddScoped<IImportService, ImportService>();
// Runs the real browse query every few minutes so the first visitor after a quiet spell doesn't
// pay the cold-connection cost for everyone (known-issues C).
builder.Services.AddHostedService<KeepWarmService>();

// Reads a YouTube video's own chapters when a clip is added. Short timeout and a browser-ish
// UA: the watch page is the only place chapters are published, and a slow lookup must not
// hold up the form. The consent cookies keep EU requests off the interstitial page.
builder.Services.AddHttpClient<IYoutubeChapterService, YoutubeChapterService>(client =>
{
    client.BaseAddress = new Uri("https://www.youtube.com");
    client.Timeout = TimeSpan.FromSeconds(10);
    client.DefaultRequestHeaders.Add("User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36");
    client.DefaultRequestHeaders.Add("Accept-Language", "en-US,en;q=0.9");
    client.DefaultRequestHeaders.Add("Cookie", "CONSENT=YES+cb; SOCS=CAI");
});

// Social sign-in. Each provider is registered against the shared IExternalAuthProvider contract
// so ExternalAuthService can enumerate whichever ones actually have credentials — an unconfigured
// provider is simply absent from /auth/external/providers and gets no button.
builder.Services.AddSingleton<OAuthStateProtector>();
builder.Services.AddScoped<IExternalAuthService, ExternalAuthService>();
builder.Services.AddHttpClient<GoogleAuthProvider>();
builder.Services.AddHttpClient<FacebookAuthProvider>();
builder.Services.AddScoped<IExternalAuthProvider>(sp => sp.GetRequiredService<GoogleAuthProvider>());
builder.Services.AddScoped<IExternalAuthProvider>(sp => sp.GetRequiredService<FacebookAuthProvider>());

builder.Services.AddHttpClient<IOllamaService, OllamaService>(client =>
{
    var baseUrl = builder.Configuration["Ollama:BaseUrl"] ?? "http://localhost:11434";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromSeconds(120);
});

var jwtKey = builder.Configuration["Jwt:Key"];
// Refuse to boot a non-Development environment with a missing or insecure signing key —
// the committed default is a dev-only placeholder; prod must supply a strong Jwt__Key.
if (string.IsNullOrWhiteSpace(jwtKey) ||
    (!builder.Environment.IsDevelopment() && (jwtKey.Length < 32 || jwtKey.Contains("dev-insecure", StringComparison.Ordinal))))
{
    throw new InvalidOperationException(
        "Jwt:Key is missing or insecure. Set a strong Jwt__Key (>= 32 chars) via environment configuration before running outside Development.");
}
// Same idea for the public base URLs, which only matter once a social provider is configured.
// A provider set up in production against the committed localhost defaults would build a
// redirect_uri the provider rejects, and — worse — bounce real users to localhost after consent.
// Fail at boot instead of at the moment someone tries to sign in.
var socialConfigured =
    !string.IsNullOrWhiteSpace(builder.Configuration["Authentication:Google:ClientId"]) ||
    !string.IsNullOrWhiteSpace(builder.Configuration["Authentication:Facebook:AppId"]);
if (socialConfigured && !builder.Environment.IsDevelopment())
{
    foreach (var key in new[] { "App:ApiUrl", "App:UiUrl" })
    {
        var value = builder.Configuration[key];
        if (string.IsNullOrWhiteSpace(value) || value.Contains("localhost", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException(
                $"{key} is missing or still points at localhost, but a social sign-in provider is " +
                $"configured. Set {key.Replace(":", "__", StringComparison.Ordinal)} " +
                "(e.g. App__UiUrl=https://dance.takelord.com) via environment configuration.");
        }
    }
}

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"],
            ValidAudience = builder.Configuration["Jwt:Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey))
        };

        // Signature and expiry are not enough on their own: tokens live 30 days, so a password
        // change or reset has to be able to retire the ones already out there. UserTokenGuard
        // compares the token's issue time against the account's cutoff (cached, so this is not
        // a database round-trip per request).
        options.Events = new JwtBearerEvents
        {
            OnTokenValidated = async context =>
            {
                var principal = context.Principal!;
                if (!int.TryParse(principal.FindFirstValue(ClaimTypes.NameIdentifier), out var userId))
                {
                    context.Fail("Token carries no user id.");
                    return;
                }

                // "iat" is seconds since the epoch; a token without one predates this check and
                // is treated as issued at the epoch, i.e. retired by any cutoff at all.
                var issuedAt = long.TryParse(principal.FindFirstValue(JwtRegisteredClaimNames.Iat), out var iat)
                    ? DateTimeOffset.FromUnixTimeSeconds(iat).UtcDateTime
                    : DateTime.UnixEpoch;

                var guard = context.HttpContext.RequestServices.GetRequiredService<IUserTokenGuard>();
                if (!await guard.IsCurrentAsync(userId, issuedAt))
                    context.Fail("Token was issued before this account's credentials changed.");
            }
        };
    });

builder.Services.AddCors(options =>
    options.AddDefaultPolicy(policy =>
        policy.WithOrigins(builder.Configuration["Cors:Origin"] ?? "http://localhost:4200")
              .AllowAnyHeader()
              .AllowAnyMethod()));

var app = builder.Build();

app.UseForwardedHeaders();
app.UseSecurityHeaders();

// Unhandled exceptions become RFC-7807 ProblemDetails instead of leaking stack traces.
app.UseExceptionHandler();

app.UseResponseCompression();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors();
app.UseAuthentication();
// After authentication so an authenticated caller is throttled per account rather than
// sharing a bucket with everyone else behind the same address.
app.UseRateLimiter();
app.UseAuthorization();
app.MapControllers();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    await db.Database.MigrateAsync();
    await SeedData.SeedAsync(db);
    // Roadmaps are authored content, so this runs every boot (not only on an empty DB) — it
    // re-syncs edited paths and re-links steps to moves that have since been added.
    await RoadmapSeeder.SeedAsync(
        db,
        app.Environment.ContentRootPath,
        scope.ServiceProvider.GetRequiredService<ILoggerFactory>().CreateLogger(nameof(RoadmapSeeder)));
}

app.Run();
