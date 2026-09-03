namespace DancePlatform.API;

/// <summary>
/// Response headers for the API's own replies. Deliberately the conservative set that is safe on
/// a JSON API and needs no per-endpoint thought:
///
///   • nosniff       — an API response is never something to content-sniff into script.
///   • DENY framing  — nothing here is meant to be embedded in someone else's page.
///   • no-referrer   — reset links and tokens travel over these paths; the URL should not leak
///                     onward through a Referer header.
///
/// The SPA's own headers (HSTS, a CSP that has to allow the YouTube/TikTok/Instagram players)
/// belong in the Apache vhost that serves /var/www/dance, not here — this middleware never sees
/// those responses.
/// </summary>
public static class SecurityHeaders
{
    public static IApplicationBuilder UseSecurityHeaders(this IApplicationBuilder app) =>
        app.Use(async (context, next) =>
        {
            // OnStarting, not a straight assignment: headers set here would otherwise be lost on
            // any path that has already begun writing the response.
            context.Response.OnStarting(() =>
            {
                var headers = context.Response.Headers;
                headers["X-Content-Type-Options"] = "nosniff";
                headers["X-Frame-Options"] = "DENY";
                headers["Referrer-Policy"] = "no-referrer";
                return Task.CompletedTask;
            });

            await next();
        });
}
