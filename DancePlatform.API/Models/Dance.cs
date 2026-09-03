namespace DancePlatform.API.Models;

public class Dance
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Slug { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime DateAdded { get; set; } = DateTime.UtcNow;

    /// <summary>
    /// Who added this. Null for the seeded/curated catalogue, which is most of it. Without this
    /// there is no way to tell whose dance a junk entry was, and POST /dances is open to any
    /// signed-in user by design (the My Dances self-service flow).
    /// </summary>
    public int? OwnerUserId { get; set; }
    public User? Owner { get; set; }

    /// <summary>
    /// "approved" or "pending". A dance added by an ordinary user is pending: reachable by its
    /// creator and by an admin, absent from browse, search, recommendations and neighbours until
    /// someone looks at it. Deliberately NOT a global query filter (unlike Video): the creator has
    /// to keep seeing their own dance in My Dances and be able to hang a video on it, and a filter
    /// that hides a row from everyone would have to be un-hidden at a dozen call sites.
    /// </summary>
    public string ReviewState { get; set; } = "approved";

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
    public ICollection<DanceInstructor> DanceInstructors { get; set; } = new List<DanceInstructor>();
    public ICollection<PracticeSessionItem> PracticeItems { get; set; } = new List<PracticeSessionItem>();
}
