namespace DancePlatform.API.DTOs.User;

public class PublicProfileDto
{
    public int Id { get; set; }
    public string Username { get; set; } = string.Empty;
    public string Nickname { get; set; } = string.Empty;
    public string? AvatarUrl { get; set; }
    public List<DanceRef> LearnedDances { get; set; } = new();
}
