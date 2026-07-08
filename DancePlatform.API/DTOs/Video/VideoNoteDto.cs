using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Video;

/// <summary>A timestamped note private to the requesting user.</summary>
public class VideoNoteDto
{
    public int Id { get; set; }
    public int VideoId { get; set; }
    public int TimeSeconds { get; set; }
    [Required] public string Text { get; set; } = string.Empty;
}

/// <summary>Create/update payload for a personal note.</summary>
public class SaveVideoNoteRequest
{
    [Range(0, int.MaxValue)] public int TimeSeconds { get; set; }
    [Required, MaxLength(500)] public string Text { get; set; } = string.Empty;
}
