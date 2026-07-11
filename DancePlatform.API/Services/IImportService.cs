using DancePlatform.API.DTOs.Import;
using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

/// <summary>Outcome of importing a single YouTube video onto a dance.</summary>
public enum ImportVideoResult { Success, InvalidUrl, DanceNotFound, Duplicate }

public interface IImportService
{
    Task<BulkImportResult> ImportDancesAsync(BulkImportRequest request);
    Task<(ImportVideoResult Result, VideoDto? Video)> ImportYoutubeVideoAsync(YoutubeVideoImportRequest request);
}
