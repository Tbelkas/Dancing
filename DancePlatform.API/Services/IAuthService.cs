using DancePlatform.API.DTOs.Auth;

namespace DancePlatform.API.Services;

public enum RegisterResult { Ok, UsernameTaken, EmailTaken }

public interface IAuthService
{
    Task<AuthResponse?> LoginAsync(LoginRequest request);
    Task<(RegisterResult Result, AuthResponse? Response)> RegisterAsync(RegisterRequest request);

    /// <summary>
    /// Issues a reset link if — and only if — that address belongs to an account. Returns
    /// nothing either way: the caller must answer identically for a known and an unknown
    /// address, or this endpoint becomes a way to test whether someone has an account here.
    /// </summary>
    Task RequestPasswordResetAsync(string email, CancellationToken ct = default);

    /// <summary>Spends a reset token. Null when it is unknown, expired, or already used.</summary>
    Task<AuthResponse?> ResetPasswordAsync(ResetPasswordRequest request);

    /// <summary>Changes a signed-in user's password. The returned response carries a fresh
    /// token, because setting a new password invalidates every token issued before it —
    /// including the one the caller made this request with.</summary>
    Task<(PasswordChangeResult Result, AuthResponse? Response)> ChangePasswordAsync(int userId, ChangePasswordRequest request);
}
