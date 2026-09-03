using DancePlatform.API.Services;
using Microsoft.Extensions.Caching.Memory;
using Xunit;

namespace DancePlatform.Tests;

public class LoginThrottleTests
{
    private static LoginThrottle NewThrottle() =>
        new(new MemoryCache(new MemoryCacheOptions()));

    [Fact]
    public void AFewTyposDoNotLockAnyoneOut()
    {
        var throttle = NewThrottle();
        for (var i = 0; i < LoginThrottle.MaxFailures - 1; i++)
            throttle.RecordFailure("1.2.3.4", "justas");

        Assert.False(throttle.IsLockedOut("1.2.3.4", "justas"));
    }

    [Fact]
    public void RepeatedFailuresFromOneAddressLockItOut()
    {
        var throttle = NewThrottle();
        for (var i = 0; i < LoginThrottle.MaxFailures; i++)
            throttle.RecordFailure("1.2.3.4", $"victim{i}");

        // Different account each time — a password list walked from one machine still stops.
        Assert.True(throttle.IsLockedOut("1.2.3.4", "someone-else"));
    }

    [Fact]
    public void RepeatedFailuresAgainstOneAccountLockItOut()
    {
        var throttle = NewThrottle();
        for (var i = 0; i < LoginThrottle.MaxFailures; i++)
            throttle.RecordFailure($"10.0.0.{i}", "justas");

        // Different address each time — a distributed run converging on one account still stops.
        Assert.True(throttle.IsLockedOut("203.0.113.9", "justas"));
    }

    [Fact]
    public void CasingDoesNotMintAFreshBudget()
    {
        var throttle = NewThrottle();
        for (var i = 0; i < LoginThrottle.MaxFailures; i++)
            throttle.RecordFailure($"10.0.0.{i}", "JuStAs");

        Assert.True(throttle.IsLockedOut("203.0.113.9", "justas"));
    }

    [Fact]
    public void TheRightPasswordClearsTheCounters()
    {
        var throttle = NewThrottle();
        for (var i = 0; i < LoginThrottle.MaxFailures - 1; i++)
            throttle.RecordFailure("1.2.3.4", "justas");

        throttle.RecordSuccess("1.2.3.4", "justas");
        for (var i = 0; i < LoginThrottle.MaxFailures - 1; i++)
            throttle.RecordFailure("1.2.3.4", "justas");

        // Without the reset, the second run of typos would have tipped it over.
        Assert.False(throttle.IsLockedOut("1.2.3.4", "justas"));
    }
}
