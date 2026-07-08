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

    /// <summary>Edits a session's date/notes (and duration when it holds a single dance). Null when not found.</summary>
    Task<PracticeSessionDto?> UpdateAsync(int userId, int id, UpdatePracticeSessionRequest request);

    /// <summary>
    /// Learned dances the user hasn't practiced recently, stalest first — the spaced-repetition
    /// review queue. A dance falls off the queue as soon as it's practiced again.
    /// </summary>
    Task<List<ReviewDanceDto>> GetReviewQueueAsync(int userId);

    Task<bool> DeleteAsync(int userId, int id);
}
