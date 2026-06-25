using DancePlatform.API.DTOs.Practice;

namespace DancePlatform.API.Services;

public interface IPracticeService
{
    Task<List<PracticeSessionDto>> GetAsync(int userId);
    Task<PracticeSessionDto?> CreateAsync(int userId, CreatePracticeSessionRequest request);

    /// <summary>
    /// Folds watch time into the user's live session, or opens a new one once the 10-minute
    /// continuation buffer has lapsed. Returns the affected session, or null if the dance is unknown.
    /// </summary>
    Task<PracticeSessionDto?> HeartbeatAsync(int userId, PracticeHeartbeatRequest request);

    Task<bool> DeleteAsync(int userId, int id);
}
