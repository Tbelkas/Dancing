namespace DancePlatform.API.Models;

public class User
{
    public int Id { get; set; }
    public string Username { get; set; } = string.Empty;
    /// Empty for accounts created through an external provider — they have no password to verify.
    /// AuthService.LoginAsync must treat an empty hash as "not a password account" rather than
    /// letting BCrypt decide.
    public string PasswordHash { get; set; } = string.Empty;
    /// Reported by an external provider at sign-up; null for accounts registered with a password.
    public string? Email { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Nickname { get; set; } = string.Empty;
    public bool IsAdmin { get; set; } = false;
    public string? AvatarUrl { get; set; }
    public ProfileVisibility Visibility { get; set; } = ProfileVisibility.Private;
    /// Prefer the platform's own player controls (beta) over the embed's native ones where the embed allows it.
    public bool UseBetaViewer { get; set; } = false;
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public ICollection<UserLogin> Logins { get; set; } = new List<UserLogin>();
    public ICollection<UserFavoriteDance> FavoriteDances { get; set; } = new List<UserFavoriteDance>();
    public ICollection<UserLearnedDance> LearnedDances { get; set; } = new List<UserLearnedDance>();
    public ICollection<UserInProgressDance> InProgressDances { get; set; } = new List<UserInProgressDance>();
    public ICollection<UserMyStyle> MyStyles { get; set; } = new List<UserMyStyle>();
    public ICollection<VideoRating> Ratings { get; set; } = new List<VideoRating>();
    public ICollection<PracticeSession> PracticeSessions { get; set; } = new List<PracticeSession>();
}

public enum ProfileVisibility { Public, Private }
