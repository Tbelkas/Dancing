using DancePlatform.API.DTOs.Instructor;

namespace DancePlatform.API.Services;

public interface IInstructorService
{
    Task<List<InstructorDto>> GetAllAsync();
    Task<InstructorDto?> GetByIdAsync(int id);
    Task<InstructorDto> CreateAsync(CreateInstructorRequest request);
    Task<bool> DeleteAsync(int id);
}
