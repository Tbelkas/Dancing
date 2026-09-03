using DancePlatform.API;
using DancePlatform.API.DTOs.Auth;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[EnableRateLimiting(RateLimitPolicies.Auth)]
public class AuthController : ControllerBase
{
    private readonly IAuthService _authService;
    private readonly ILoginThrottle _throttle;

    public AuthController(IAuthService authService, ILoginThrottle throttle)
    {
        _authService = authService;
        _throttle = throttle;
    }

    [HttpPost("login")]
    [EnableRateLimiting(RateLimitPolicies.Login)]
    public async Task<IActionResult> Login([FromBody] LoginRequest request)
    {
        var ip = ClientAddress();
        if (_throttle.IsLockedOut(ip, request.Username))
        {
            // Same wording as a wrong password, plus a 429, so this never becomes a way to
            // discover which usernames exist by watching who gets locked out.
            Response.Headers.RetryAfter = ((int)LoginThrottle.Window.TotalSeconds).ToString();
            return StatusCode(StatusCodes.Status429TooManyRequests,
                new { message = "Too many sign-in attempts. Try again in a few minutes." });
        }

        var result = await _authService.LoginAsync(request);
        if (result is null)
        {
            _throttle.RecordFailure(ip, request.Username);
            return Unauthorized(new { message = "Invalid username or password." });
        }

        _throttle.RecordSuccess(ip, request.Username);
        return Ok(result);
    }

    [HttpPost("register")]
    public async Task<IActionResult> Register([FromBody] RegisterRequest request)
    {
        var result = await _authService.RegisterAsync(request);
        if (result is null)
            return Conflict(new { message = "Username already taken." });
        return CreatedAtAction(nameof(Login), result);
    }

    private string ClientAddress() =>
        HttpContext.Connection.RemoteIpAddress?.ToString() ?? "unknown";
}
