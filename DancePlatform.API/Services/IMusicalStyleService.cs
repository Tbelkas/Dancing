using DancePlatform.API.DTOs.MusicalStyle;

namespace DancePlatform.API.Services;

public interface IMusicalStyleService
{
    Task<List<MusicalStyleDto>> GetAllAsync();
    Task<MusicalStyleDto?> GetByIdAsync(int id);
    Task<MusicalStyleDto> CreateAsync(CreateMusicalStyleRequest request);
    Task<bool> DeleteAsync(int id);
}
