namespace DancePlatform.API.Services;

/// <summary>
/// Keeps the first visitor after a quiet spell from paying for everyone else's idleness.
///
/// The known 2–4s pause on the first request after idle (known-issues C) is the connection pool
/// having emptied and the query path having gone cold. This runs the actual first page of browse
/// — not a ping — every few minutes, so the pool has a live connection, the compiled query is
/// still compiled, and the catalogue-size cache is populated when a real request arrives.
///
/// Deliberately in-process rather than a cron job or systemd timer on the Pi: it deploys with the
/// application, so there is nothing to remember to install on a rebuild, and nothing to notice has
/// silently stopped.
/// </summary>
public class KeepWarmService : BackgroundService
{
    /// Under the pool's idle timeout, and far under any sensible expectation of "quiet".
    private static readonly TimeSpan Interval = TimeSpan.FromMinutes(4);

    private readonly IServiceScopeFactory _scopes;
    private readonly ILogger<KeepWarmService> _log;

    public KeepWarmService(IServiceScopeFactory scopes, ILogger<KeepWarmService> log)
    {
        _scopes = scopes;
        _log = log;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(Interval);
        do
        {
            await WarmAsync(stoppingToken);
        }
        while (await SafeWaitAsync(timer, stoppingToken));
    }

    private async Task WarmAsync(CancellationToken ct)
    {
        try
        {
            // A scope of its own: DanceService and its DbContext are scoped, and a background
            // service resolving them from the root provider would hold one context forever.
            using var scope = _scopes.CreateScope();
            var dances = scope.ServiceProvider.GetRequiredService<IDanceService>();
            await dances.SearchAsync("", null, null, null, null, "recommended", null, page: 1, pageSize: 24);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            // Never fatal. A database that is down is the health endpoint's story to tell; this
            // one just tries again in a few minutes.
            _log.LogDebug(ex, "Keep-warm query failed; will retry.");
        }
    }

    private static async Task<bool> SafeWaitAsync(PeriodicTimer timer, CancellationToken ct)
    {
        try
        {
            return await timer.WaitForNextTickAsync(ct);
        }
        catch (OperationCanceledException)
        {
            // Shutdown, not a failure.
            return false;
        }
    }
}
