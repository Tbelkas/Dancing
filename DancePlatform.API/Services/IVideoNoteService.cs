using DancePlatform.API.DTOs.Video;

namespace DancePlatform.API.Services;

public interface IVideoNoteService
{
    /// <summary>The requesting user's notes for one video, earliest first.</summary>
    Task<List<VideoNoteDto>> GetForVideoAsync(int userId, int videoId);

    /// <summary>Saves a note for the user; returns the updated list, or null if the
    /// video doesn't exist or the input is invalid.</summary>
    Task<List<VideoNoteDto>?> AddAsync(int userId, int videoId, SaveVideoNoteRequest note);

    /// <summary>Rewrites one of the user's own notes (time and text); returns the updated
    /// list, or null if no matching note is owned by the user or the input is invalid.</summary>
    Task<List<VideoNoteDto>?> UpdateAsync(int userId, int videoId, int noteId, SaveVideoNoteRequest note);

    /// <summary>Deletes one of the user's own notes; returns the updated list, or null
    /// if no matching note is owned by the user.</summary>
    Task<List<VideoNoteDto>?> DeleteAsync(int userId, int videoId, int noteId);
}
