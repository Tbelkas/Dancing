using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Auth;

public class ForgotPasswordRequest
{
    [Required, EmailAddress] public string Email { get; set; } = string.Empty;
}

public class ResetPasswordRequest
{
    [Required] public string Token { get; set; } = string.Empty;
    [Required, MinLength(8)] public string NewPassword { get; set; } = string.Empty;
}

public class ChangePasswordRequest
{
    /// Empty for an account that has no password yet (created through Google/Facebook and
    /// setting one for the first time).
    public string CurrentPassword { get; set; } = string.Empty;
    [Required, MinLength(8)] public string NewPassword { get; set; } = string.Empty;
}

public enum PasswordChangeResult
{
    Ok,
    UserNotFound,
    WrongCurrentPassword
}
