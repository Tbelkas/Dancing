namespace DancePlatform.API.DTOs.User;

public class UserProfileDto
{
    public int Id { get; set; }
    public string Username { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Nickname { get; set; } = string.Empty;
    public string? AvatarUrl { get; set; }
    public string Visibility { get; set; } = string.Empty;
    public DateTime DateAdded { get; set; }
    public List<string> FavoriteDances { get; set; } = new();
    public List<string> LearnedDances { get; set; } = new();
}
