using DancePlatform.API.Data;
using DancePlatform.API.DTOs.MusicalStyle;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class MusicalStyleService : IMusicalStyleService
{
    private readonly AppDbContext _db;

    public MusicalStyleService(AppDbContext db) => _db = db;

    public async Task<List<MusicalStyleDto>> GetAllAsync() =>
        await _db.MusicalStyles
            .Include(ms => ms.DanceMusicalStyles)
            .Select(ms => new MusicalStyleDto
            {
                Id = ms.Id,
                Name = ms.Name,
                Description = ms.Description,
                DateAdded = ms.DateAdded,
                DanceCount = ms.DanceMusicalStyles.Count
            }).ToListAsync();

    public async Task<MusicalStyleDto?> GetByIdAsync(int id) =>
        await _db.MusicalStyles
            .Include(ms => ms.DanceMusicalStyles)
            .Where(ms => ms.Id == id)
            .Select(ms => new MusicalStyleDto
            {
                Id = ms.Id,
                Name = ms.Name,
                Description = ms.Description,
                DateAdded = ms.DateAdded,
                DanceCount = ms.DanceMusicalStyles.Count
            }).FirstOrDefaultAsync();

    public async Task<MusicalStyleDto> CreateAsync(CreateMusicalStyleRequest request)
    {
        var musicalStyle = new MusicalStyle { Name = request.Name, Description = request.Description };
        _db.MusicalStyles.Add(musicalStyle);
        await _db.SaveChangesAsync();
        return (await GetByIdAsync(musicalStyle.Id))!;
    }

    public async Task<bool> DeleteAsync(int id)
    {
        var musicalStyle = await _db.MusicalStyles.FindAsync(id);
        if (musicalStyle is null) return false;
        _db.MusicalStyles.Remove(musicalStyle);
        await _db.SaveChangesAsync();
        return true;
    }
}
