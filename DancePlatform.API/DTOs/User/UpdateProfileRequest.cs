namespace DancePlatform.API.DTOs.User;

public class UpdateProfileRequest
{
    public string? Name { get; set; }
    public string? Nickname { get; set; }
    public string? AvatarUrl { get; set; }
    public string? Visibility { get; set; }
}
