using DancePlatform.API;
using DancePlatform.API.DTOs.Auth;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[EnableRateLimiting(RateLimitPolicies.Auth)]
public class AuthController : AppControllerBase
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
        var (result, response) = await _authService.RegisterAsync(request);
        return result switch
        {
            RegisterResult.UsernameTaken => Conflict(new { message = "Username already taken." }),
            RegisterResult.EmailTaken => Conflict(new { message = "That email address already has an account." }),
            _ => CreatedAtAction(nameof(Login), response)
        };
    }

    /// <summary>
    /// Always 202, whether or not the address belongs to an account. The difference between
    /// "sent" and "no such account" is exactly the thing an attacker would harvest, so the
    /// caller is told what will happen, not what did.
    /// </summary>
    [HttpPost("forgot-password")]
    public async Task<IActionResult> ForgotPassword([FromBody] ForgotPasswordRequest request, CancellationToken ct)
    {
        await _authService.RequestPasswordResetAsync(request.Email, ct);
        return Accepted(new { message = "If that address has an account, a reset link is on its way." });
    }

    [HttpPost("reset-password")]
    public async Task<IActionResult> ResetPassword([FromBody] ResetPasswordRequest request)
    {
        var result = await _authService.ResetPasswordAsync(request);
        return result is null
            ? BadRequest(new { message = "That reset link has expired or has already been used." })
            : Ok(result);
    }

    /// <summary>
    /// Returns a fresh token: changing the password retires every token issued beforehand,
    /// so the one the caller authenticated with is dead by the time this responds.
    /// </summary>
    [Authorize]
    [HttpPost("change-password")]
    public async Task<IActionResult> ChangePassword([FromBody] ChangePasswordRequest request)
    {
        var (result, response) = await _authService.ChangePasswordAsync(CurrentUserId!.Value, request);
        return result switch
        {
            PasswordChangeResult.UserNotFound => NotFound(),
            PasswordChangeResult.WrongCurrentPassword =>
                BadRequest(new { message = "Current password is incorrect." }),
            _ => Ok(response)
        };
    }

    private string ClientAddress() =>
        HttpContext.Connection.RemoteIpAddress?.ToString() ?? "unknown";
}
