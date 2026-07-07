namespace DancePlatform.API.DTOs.Dance;

/// <summary>
/// The alphabetical prev/next neighbours of a dance within its canonical style — powers the
/// dance-detail pager without the client fetching the whole style's catalog. Either side is null
/// at the ends of the style (and both are null when the dance has no style or doesn't exist).
/// </summary>
public class DanceNeighborsDto
{
    public DanceDto? Prev { get; set; }
    public DanceDto? Next { get; set; }
}
