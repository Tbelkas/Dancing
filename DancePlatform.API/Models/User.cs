namespace DancePlatform.API.Models;

public class User
{
    public int Id { get; set; }
    public string Username { get; set; } = string.Empty;
    public string PasswordHash { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Nickname { get; set; } = string.Empty;
    public string? AvatarUrl { get; set; }
    public ProfileVisibility Visibility { get; set; } = ProfileVisibility.Public;
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public ICollection<UserFavoriteDance> FavoriteDances { get; set; } = new List<UserFavoriteDance>();
    public ICollection<UserLearnedDance> LearnedDances { get; set; } = new List<UserLearnedDance>();
}

public enum ProfileVisibility { Public, Private }
