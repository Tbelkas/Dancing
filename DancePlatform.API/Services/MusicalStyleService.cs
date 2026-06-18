using System.Linq.Expressions;
using DancePlatform.API.Data;
using DancePlatform.API.DTOs.MusicalStyle;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class MusicalStyleService : IMusicalStyleService
{
    private readonly AppDbContext _db;

    public MusicalStyleService(AppDbContext db) => _db = db;

    private static readonly Expression<Func<MusicalStyle, MusicalStyleDto>> ToDto = ms => new MusicalStyleDto
    {
        Id = ms.Id,
        Name = ms.Name,
        Description = ms.Description,
        DateAdded = ms.DateAdded,
        DanceCount = ms.DanceMusicalStyles.Count
    };

    public async Task<List<MusicalStyleDto>> GetAllAsync() =>
        await _db.MusicalStyles.Include(ms => ms.DanceMusicalStyles).Select(ToDto).ToListAsync();

    public async Task<MusicalStyleDto?> GetByIdAsync(int id) =>
        await _db.MusicalStyles.Include(ms => ms.DanceMusicalStyles).Where(ms => ms.Id == id).Select(ToDto).FirstOrDefaultAsync();

    public async Task<MusicalStyleDto> CreateAsync(CreateMusicalStyleRequest request)
    {
        var ms = new MusicalStyle { Name = request.Name, Description = request.Description };
        _db.MusicalStyles.Add(ms);
        await _db.SaveChangesAsync();
        return new MusicalStyleDto { Id = ms.Id, Name = ms.Name, Description = ms.Description, DateAdded = ms.DateAdded, DanceCount = 0 };
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
