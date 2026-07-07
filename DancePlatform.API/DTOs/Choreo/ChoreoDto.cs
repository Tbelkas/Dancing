using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.DTOs.Choreo;

public class ChoreoDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string FileName { get; set; } = string.Empty;
    public int? DurationSeconds { get; set; }
    public DateTime DateAdded { get; set; }
    public List<VideoSegmentDto> Loops { get; set; } = new();
}
