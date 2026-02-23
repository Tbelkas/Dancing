using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Auth;

public class RegisterRequest
{
    [Required, MinLength(3)] public string Username { get; set; } = string.Empty;
    [Required, MinLength(8)] public string Password { get; set; } = string.Empty;
    [Required] public string Name { get; set; } = string.Empty;
    public string Nickname { get; set; } = string.Empty;
}
