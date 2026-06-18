using System.Linq.Expressions;
using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Style;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class StyleService : IStyleService
{
    private readonly AppDbContext _db;

    public StyleService(AppDbContext db) => _db = db;

    private static readonly Expression<Func<Style, StyleDto>> ToDto = s => new StyleDto
    {
        Id = s.Id,
        Name = s.Name,
        Description = s.Description,
        DateAdded = s.DateAdded,
        DanceCount = s.DanceStyles.Count
    };

    public async Task<List<StyleDto>> GetAllAsync() =>
        await _db.Styles.Include(s => s.DanceStyles).Select(ToDto).ToListAsync();

    public async Task<StyleDto?> GetByIdAsync(int id) =>
        await _db.Styles.Include(s => s.DanceStyles).Where(s => s.Id == id).Select(ToDto).FirstOrDefaultAsync();

    public async Task<StyleDto> CreateAsync(CreateStyleRequest request)
    {
        var style = new Style { Name = request.Name, Description = request.Description };
        _db.Styles.Add(style);
        await _db.SaveChangesAsync();
        return new StyleDto { Id = style.Id, Name = style.Name, Description = style.Description, DateAdded = style.DateAdded, DanceCount = 0 };
    }

    public async Task<bool> DeleteAsync(int id)
    {
        var style = await _db.Styles.FindAsync(id);
        if (style is null) return false;
        _db.Styles.Remove(style);
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<bool> ToggleMyStyleAsync(int userId, int styleId)
    {
        var existing = await _db.UserMyStyles.FindAsync(userId, styleId);
        if (existing is not null)
        {
            _db.UserMyStyles.Remove(existing);
            await _db.SaveChangesAsync();
            return false;
        }
        _db.UserMyStyles.Add(new UserMyStyle { UserId = userId, StyleId = styleId });
        await _db.SaveChangesAsync();
        return true;
    }
}
