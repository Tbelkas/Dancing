namespace DancePlatform.API.Models;

public class Dance
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Slug { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    public DifficultyLevel Difficulty { get; set; } = DifficultyLevel.None;

    public int FavoriteCount { get; set; }
    public int LearnedCount { get; set; }
    public double AverageRating { get; set; }
    public int RatingCount { get; set; }

    public ICollection<DanceStyle> DanceStyles { get; set; } = new List<DanceStyle>();
    public ICollection<DanceMusicalStyle> DanceMusicalStyles { get; set; } = new List<DanceMusicalStyle>();
    public ICollection<Video> Videos { get; set; } = new List<Video>();
    public ICollection<UserFavoriteDance> FavoritedBy { get; set; } = new List<UserFavoriteDance>();
    public ICollection<UserLearnedDance> LearnedBy { get; set; } = new List<UserLearnedDance>();
    public ICollection<UserInProgressDance> InProgressBy { get; set; } = new List<UserInProgressDance>();
    public ICollection<DanceRating> Ratings { get; set; } = new List<DanceRating>();
    public ICollection<DanceInstructor> DanceInstructors { get; set; } = new List<DanceInstructor>();
    public ICollection<PracticeSession> PracticeSessions { get; set; } = new List<PracticeSession>();
}
