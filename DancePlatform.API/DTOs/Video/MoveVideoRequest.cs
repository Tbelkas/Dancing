namespace DancePlatform.API.DTOs.Video;

/// <summary>Reassigns a video to a different dance (and thereby its style/category).</summary>
public class MoveVideoRequest
{
    public int DanceId { get; set; }
}
