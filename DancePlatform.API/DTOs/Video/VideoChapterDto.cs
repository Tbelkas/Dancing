namespace DancePlatform.API.DTOs.Video;

// A "chapter" is one dance that lives inside a shared source video. Several Video
// rows can point at the same YouTube id, each marking a different dance's segment;
// these let the player jump between those segments without leaving the page.
public class VideoChapterDto
{
    public int Id { get; set; }            // Video row id
    public int DanceId { get; set; }
    public string DanceName { get; set; } = string.Empty;
    public string DanceSlug { get; set; } = string.Empty;
    public int? StartTime { get; set; }
    public int? EndTime { get; set; }
}
