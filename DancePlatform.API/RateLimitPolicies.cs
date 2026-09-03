using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

namespace DancePlatform.API;

/// <summary>
/// Request throttling. Everything here partitions on the caller's IP, which only means
/// anything because <c>UseForwardedHeaders</c> runs first — Apache reverse-proxies to
/// Kestrel from localhost, so without it every visitor would share one bucket and the
/// first busy minute would lock out the whole site.
/// </summary>
public static class RateLimitPolicies
{
    /// <summary>Account-creating and account-recovering endpoints: register, forgot, reset.</summary>
    public const string Auth = "auth";

    /// <summary>
    /// A volume ceiling on sign-in. Guessing is handled by <see cref="Services.LoginThrottle"/>,
    /// which counts failures — a limit tight enough to stop a dictionary run here would also
    /// stop a household, an office, and the e2e suite, all of which sign in successfully and
    /// often from one address.
    /// </summary>
    public const string Login = "login";

    /// <summary>The anonymous view-count bump, which feeds the "recommended" ranking.</summary>
    public const string Views = "views";

    public static IServiceCollection AddAppRateLimiting(this IServiceCollection services) =>
        services.AddRateLimiter(options =>
        {
            options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
            options.OnRejected = (context, _) =>
            {
                // Tell a well-behaved client when to come back. The window is fixed, so the
                // longest anyone waits is the window itself.
                context.HttpContext.Response.Headers.RetryAfter = "60";
                return ValueTask.CompletedTask;
            };

            // A coarse ceiling over everything, sized so a normal browsing session (each page
            // is several API calls) never notices, but a script hammering the Pi's SD card does.
            options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(context =>
                RateLimitPartition.GetFixedWindowLimiter(ClientKey(context), _ => new FixedWindowRateLimiterOptions
                {
                    PermitLimit = 600,
                    Window = TimeSpan.FromMinutes(1)
                }));

            // Nobody legitimately creates ten accounts, or asks for ten reset mails, in five
            // minutes — and each reset request costs an outbound email.
            options.AddPolicy(Auth, context =>
                RateLimitPartition.GetFixedWindowLimiter(ClientKey(context), _ => new FixedWindowRateLimiterOptions
                {
                    PermitLimit = 10,
                    Window = TimeSpan.FromMinutes(5)
                }));

            // Sized for many *successful* sign-ins from one address (a full e2e run is ~17,
            // a shared network more). It exists to bound BCrypt work, not to catch guessing.
            options.AddPolicy(Login, context =>
                RateLimitPartition.GetFixedWindowLimiter(ClientKey(context), _ => new FixedWindowRateLimiterOptions
                {
                    PermitLimit = 60,
                    Window = TimeSpan.FromMinutes(5)
                }));

            // One person watching videos bumps this a handful of times a minute. The limit is
            // what stops a loop from promoting a video to the top of "recommended".
            options.AddPolicy(Views, context =>
                RateLimitPartition.GetFixedWindowLimiter(ClientKey(context), _ => new FixedWindowRateLimiterOptions
                {
                    PermitLimit = 30,
                    Window = TimeSpan.FromMinutes(1)
                }));
        });

    /// <summary>
    /// The partition key: the signed-in user where there is one, otherwise the remote IP.
    /// Keying authenticated traffic by user id means a household behind one NAT address
    /// doesn't share a bucket, while anonymous traffic still can't dodge the limit by
    /// rotating anything cheaper than an address.
    /// </summary>
    private static string ClientKey(HttpContext context)
    {
        var userId = context.User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
        if (!string.IsNullOrEmpty(userId)) return $"u:{userId}";
        return $"ip:{context.Connection.RemoteIpAddress?.ToString() ?? "unknown"}";
    }
}
