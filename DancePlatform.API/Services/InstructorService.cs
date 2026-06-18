using System.Linq.Expressions;
using DancePlatform.API.Data;
using DancePlatform.API.DTOs.Instructor;
using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Services;

public class InstructorService : IInstructorService
{
    private readonly AppDbContext _db;

    public InstructorService(AppDbContext db) => _db = db;

    private static readonly Expression<Func<Instructor, InstructorDto>> ToDto = i => new InstructorDto
    {
        Id = i.Id,
        Name = i.Name,
        Bio = i.Bio,
        AvatarUrl = i.AvatarUrl,
        Website = i.Website,
        DanceCount = i.DanceInstructors.Count
    };

    public async Task<List<InstructorDto>> GetAllAsync() =>
        await _db.Instructors.Include(i => i.DanceInstructors).Select(ToDto).ToListAsync();

    public async Task<InstructorDto?> GetByIdAsync(int id) =>
        await _db.Instructors.Include(i => i.DanceInstructors).Where(i => i.Id == id).Select(ToDto).FirstOrDefaultAsync();

    public async Task<InstructorDto> CreateAsync(CreateInstructorRequest request)
    {
        var instructor = new Instructor
        {
            Name = request.Name,
            Bio = request.Bio,
            AvatarUrl = request.AvatarUrl,
            Website = request.Website
        };
        _db.Instructors.Add(instructor);
        await _db.SaveChangesAsync();
        return new InstructorDto { Id = instructor.Id, Name = instructor.Name, Bio = instructor.Bio, AvatarUrl = instructor.AvatarUrl, Website = instructor.Website, DanceCount = 0 };
    }

    public async Task<bool> DeleteAsync(int id)
    {
        var instructor = await _db.Instructors.FindAsync(id);
        if (instructor is null) return false;
        _db.Instructors.Remove(instructor);
        await _db.SaveChangesAsync();
        return true;
    }
}
