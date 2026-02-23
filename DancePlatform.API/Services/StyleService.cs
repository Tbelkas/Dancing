using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Style;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class StyleService : IStyleService
{
    private readonly AppDbContext _db;

    public StyleService(AppDbContext db) => _db = db;

    public async Task<List<StyleDto>> GetAllAsync() =>
        await _db.Styles
            .Include(s => s.DanceStyles)
            .Select(s => new StyleDto
            {
                Id = s.Id,
                Name = s.Name,
                Description = s.Description,
                DateAdded = s.DateAdded,
                DanceCount = s.DanceStyles.Count
            }).ToListAsync();

    public async Task<StyleDto?> GetByIdAsync(int id) =>
        await _db.Styles
            .Include(s => s.DanceStyles)
            .Where(s => s.Id == id)
            .Select(s => new StyleDto
            {
                Id = s.Id,
                Name = s.Name,
                Description = s.Description,
                DateAdded = s.DateAdded,
                DanceCount = s.DanceStyles.Count
            }).FirstOrDefaultAsync();

    public async Task<StyleDto> CreateAsync(CreateStyleRequest request)
    {
        var style = new Style { Name = request.Name, Description = request.Description };
        _db.Styles.Add(style);
        await _db.SaveChangesAsync();
        return (await GetByIdAsync(style.Id))!;
    }

    public async Task<bool> DeleteAsync(int id)
    {
        var style = await _db.Styles.FindAsync(id);
        if (style is null) return false;
        _db.Styles.Remove(style);
        await _db.SaveChangesAsync();
        return true;
    }
}
