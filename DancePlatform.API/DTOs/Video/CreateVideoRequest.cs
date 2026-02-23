using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Video;

public class CreateVideoRequest
{
    [Required] public string Title { get; set; } = string.Empty;
    [Required] public string YouTubeId { get; set; } = string.Empty;
    public string? Description { get; set; }
    [Required] public int DanceId { get; set; }
}
