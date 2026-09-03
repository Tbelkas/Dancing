using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Dance;

public class CreateDanceRequest
{
    [Required, MinLength(2)] public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string Difficulty { get; set; } = "None";
    public List<int> StyleIds { get; set; } = new();
    public List<int> MusicalStyleIds { get; set; } = new();
    public List<int> InstructorIds { get; set; } = new();
}

public class ReviewDanceRequest
{
    /// "approved" puts the dance into the public catalogue; anything else holds it.
    [Required] public string ReviewState { get; set; } = string.Empty;
}
