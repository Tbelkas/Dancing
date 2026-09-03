namespace DancePlatform.API.DTOs.User;

public record DanceRef(int Id, string Name, string Slug, string StyleSlug);

public class UserProfileDto
{
    public int Id { get; set; }
    public string Username { get; set; } = string.Empty;
    /// Null for accounts created before the address was collected. The profile page prompts
    /// for one, because without it the account cannot be recovered.
    public string? Email { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Nickname { get; set; } = string.Empty;
    public string? AvatarUrl { get; set; }
    public string Visibility { get; set; } = string.Empty;
    public bool UseBetaViewer { get; set; }
    public DateTime DateAdded { get; set; }
    public List<DanceRef> FavoriteDances { get; set; } = new();
    public List<DanceRef> LearnedDances { get; set; } = new();
    public List<DanceRef> InProgressDances { get; set; } = new();
}
