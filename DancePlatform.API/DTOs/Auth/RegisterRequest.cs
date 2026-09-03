using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Auth;

public class RegisterRequest
{
    [Required, MinLength(3)] public string Username { get; set; } = string.Empty;
    /// Required, and the only route back into an account whose password is forgotten — there is
    /// no other channel to the user. Accounts created before this field existed have none, and
    /// are prompted to add one from their profile.
    [Required, EmailAddress] public string Email { get; set; } = string.Empty;
    [Required, MinLength(8)] public string Password { get; set; } = string.Empty;
    [Required] public string Name { get; set; } = string.Empty;
    public string Nickname { get; set; } = string.Empty;
}
