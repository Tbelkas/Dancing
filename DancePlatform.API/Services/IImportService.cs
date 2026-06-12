using DancePlatform.API.DTOs.Import;
using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

public interface IImportService
{
    Task<BulkImportResult> ImportDancesAsync(BulkImportRequest request);
    Task<VideoDto?> ImportYoutubeVideoAsync(YoutubeVideoImportRequest request);
}
