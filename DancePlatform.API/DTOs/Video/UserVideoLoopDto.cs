using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Video;

/// <summary>A loop region private to the requesting user.</summary>
public class UserVideoLoopDto
{
    public int Id { get; set; }
    public int VideoId { get; set; }
    [Required] public string Label { get; set; } = string.Empty;
    public int StartTime { get; set; }
    public int? EndTime { get; set; }
}
