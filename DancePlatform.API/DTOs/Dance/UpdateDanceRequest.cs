namespace DancePlatform.API.DTOs.Dance;

public class UpdateDanceRequest
{
    public string? Name { get; set; }
    public string? Description { get; set; }
    public string? Difficulty { get; set; }
    public List<int>? StyleIds { get; set; }
    public List<int>? MusicalStyleIds { get; set; }
    public List<int>? InstructorIds { get; set; }
}
