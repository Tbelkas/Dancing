using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.User;

public class SetEmailRequest
{
    [Required, EmailAddress] public string Email { get; set; } = string.Empty;
}

public class DeleteAccountRequest
{
    /// Empty is legitimate for a provider-only account, which has no password to give.
    public string Password { get; set; } = string.Empty;
}

public class UpdateProfileRequest
{
    public string? Name { get; set; }
    public string? Nickname { get; set; }
    public string? AvatarUrl { get; set; }
    public string? Visibility { get; set; }
    public bool? UseBetaViewer { get; set; }
}
