using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class VideoNoteService : IVideoNoteService
{
    private readonly AppDbContext _db;

    public VideoNoteService(AppDbContext db) => _db = db;

    public Task<List<VideoNoteDto>> GetForVideoAsync(int userId, int videoId) =>
        QueryFor(userId, videoId).ToListAsync();

    public async Task<List<VideoNoteDto>?> AddAsync(int userId, int videoId, SaveVideoNoteRequest note)
    {
        if (string.IsNullOrWhiteSpace(note.Text) || note.TimeSeconds < 0) return null;
        if (!await _db.Videos.AnyAsync(v => v.Id == videoId)) return null;

        _db.VideoNotes.Add(new VideoNote
        {
            UserId = userId,
            VideoId = videoId,
            TimeSeconds = note.TimeSeconds,
            Text = note.Text.Trim()
        });
        await _db.SaveChangesAsync();
        return await GetForVideoAsync(userId, videoId);
    }

    public async Task<List<VideoNoteDto>?> UpdateAsync(int userId, int videoId, int noteId, SaveVideoNoteRequest note)
    {
        if (string.IsNullOrWhiteSpace(note.Text) || note.TimeSeconds < 0) return null;

        var existing = await _db.VideoNotes
            .FirstOrDefaultAsync(n => n.Id == noteId && n.UserId == userId && n.VideoId == videoId);
        if (existing is null) return null;

        existing.TimeSeconds = note.TimeSeconds;
        existing.Text = note.Text.Trim();
        await _db.SaveChangesAsync();
        return await GetForVideoAsync(userId, videoId);
    }

    public async Task<List<VideoNoteDto>?> DeleteAsync(int userId, int videoId, int noteId)
    {
        var existing = await _db.VideoNotes
            .FirstOrDefaultAsync(n => n.Id == noteId && n.UserId == userId && n.VideoId == videoId);
        if (existing is null) return null;

        _db.VideoNotes.Remove(existing);
        await _db.SaveChangesAsync();
        return await GetForVideoAsync(userId, videoId);
    }

    private IQueryable<VideoNoteDto> QueryFor(int userId, int videoId) =>
        _db.VideoNotes
            .Where(n => n.UserId == userId && n.VideoId == videoId)
            .OrderBy(n => n.TimeSeconds).ThenBy(n => n.Id)
            .Select(n => new VideoNoteDto
            {
                Id = n.Id,
                VideoId = n.VideoId,
                TimeSeconds = n.TimeSeconds,
                Text = n.Text
            });
}
