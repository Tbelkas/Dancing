using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Video;

public class CreateVideoRequest
{
    [Required] public string Title { get; set; } = string.Empty;
    [Required] public string VideoId { get; set; } = string.Empty;
    public string Platform { get; set; } = "youtube";
    public string? Description { get; set; }
    [Required] public int DanceId { get; set; }
    public int? StartTime { get; set; }
    public int? EndTime { get; set; }
}
