using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Dance;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class DanceService : IDanceService
{
    private readonly AppDbContext _db;

    public DanceService(AppDbContext db) => _db = db;

    public async Task<List<DanceDto>> GetAllAsync(int? userId) =>
        await BuildQuery(userId).ToListAsync();

    public async Task<DanceDto?> GetByIdAsync(int id, int? userId) =>
        await BuildQuery(userId).FirstOrDefaultAsync(d => d.Id == id);

    public async Task<DanceDto> CreateAsync(CreateDanceRequest request)
    {
        var dance = new Dance { Name = request.Name, Description = request.Description };
        _db.Dances.Add(dance);
        await _db.SaveChangesAsync();

        foreach (var styleId in request.StyleIds)
            _db.DanceStyles.Add(new DanceStyle { DanceId = dance.Id, StyleId = styleId });

        await _db.SaveChangesAsync();
        return (await GetByIdAsync(dance.Id, null))!;
    }

    public async Task<DanceDto?> UpdateAsync(int id, UpdateDanceRequest request)
    {
        var dance = await _db.Dances.Include(d => d.DanceStyles).FirstOrDefaultAsync(d => d.Id == id);
        if (dance is null) return null;

        if (request.Name is not null) dance.Name = request.Name;
        if (request.Description is not null) dance.Description = request.Description;

        if (request.StyleIds is not null)
        {
            _db.DanceStyles.RemoveRange(dance.DanceStyles);
            foreach (var styleId in request.StyleIds)
                _db.DanceStyles.Add(new DanceStyle { DanceId = dance.Id, StyleId = styleId });
        }

        await _db.SaveChangesAsync();
        return await GetByIdAsync(id, null);
    }

    public async Task<bool> DeleteAsync(int id)
    {
        var dance = await _db.Dances.FindAsync(id);
        if (dance is null) return false;
        _db.Dances.Remove(dance);
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<bool> ToggleFavoriteAsync(int userId, int danceId)
    {
        var existing = await _db.UserFavoriteDances.FindAsync(userId, danceId);
        if (existing is not null)
        {
            _db.UserFavoriteDances.Remove(existing);
            await _db.SaveChangesAsync();
            return false;
        }
        _db.UserFavoriteDances.Add(new UserFavoriteDance { UserId = userId, DanceId = danceId });
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<bool> ToggleLearnedAsync(int userId, int danceId)
    {
        var existing = await _db.UserLearnedDances.FindAsync(userId, danceId);
        if (existing is not null)
        {
            _db.UserLearnedDances.Remove(existing);
            await _db.SaveChangesAsync();
            return false;
        }
        _db.UserLearnedDances.Add(new UserLearnedDance { UserId = userId, DanceId = danceId });
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<List<DanceDto>> SearchAsync(string query, int? styleId, int? userId)
    {
        var q = BuildQuery(userId);
        if (!string.IsNullOrWhiteSpace(query))
            q = q.Where(d => d.Name.ToLower().Contains(query.ToLower()));
        if (styleId.HasValue)
            q = q.Where(d => d.Styles.Any());
        return await q.ToListAsync();
    }

    private IQueryable<DanceDto> BuildQuery(int? userId) =>
        _db.Dances
            .Include(d => d.DanceStyles).ThenInclude(ds => ds.Style)
            .Include(d => d.Videos)
            .Include(d => d.FavoritedBy)
            .Include(d => d.LearnedBy)
            .Select(d => new DanceDto
            {
                Id = d.Id,
                Name = d.Name,
                Description = d.Description,
                DateAdded = d.DateAdded,
                Styles = d.DanceStyles.Select(ds => ds.Style.Name).ToList(),
                VideoCount = d.Videos.Count,
                IsFavorite = userId.HasValue && d.FavoritedBy.Any(f => f.UserId == userId.Value),
                IsLearned = userId.HasValue && d.LearnedBy.Any(l => l.UserId == userId.Value)
            });
}
