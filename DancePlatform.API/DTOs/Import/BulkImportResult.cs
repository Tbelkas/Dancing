using DancePlatform.API.DTOs.Dance;

namespace DancePlatform.API.DTOs.Import;

public class BulkImportResult
{
    public string? VideoId { get; set; }
    public List<DanceDto> Created { get; set; } = new();
    public List<string> Errors { get; set; } = new();
}
