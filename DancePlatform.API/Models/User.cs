namespace DancePlatform.API.Models;

public class User
{
    public int Id { get; set; }
    public string Username { get; set; } = string.Empty;
    public string PasswordHash { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Nickname { get; set; } = string.Empty;
    public bool IsAdmin { get; set; } = false;
    public string? AvatarUrl { get; set; }
    public ProfileVisibility Visibility { get; set; } = ProfileVisibility.Private;
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public ICollection<UserFavoriteDance> FavoriteDances { get; set; } = new List<UserFavoriteDance>();
    public ICollection<UserLearnedDance> LearnedDances { get; set; } = new List<UserLearnedDance>();
    public ICollection<UserInProgressDance> InProgressDances { get; set; } = new List<UserInProgressDance>();
    public ICollection<UserMyStyle> MyStyles { get; set; } = new List<UserMyStyle>();
    public ICollection<VideoRating> Ratings { get; set; } = new List<VideoRating>();
    public ICollection<PracticeSession> PracticeSessions { get; set; } = new List<PracticeSession>();
}

public enum ProfileVisibility { Public, Private }
