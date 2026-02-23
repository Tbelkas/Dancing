using DancePlatform.API.DTOs.Style;

namespace DancePlatform.API.Services;

public interface IStyleService
{
    Task<List<StyleDto>> GetAllAsync();
    Task<StyleDto?> GetByIdAsync(int id);
    Task<StyleDto> CreateAsync(CreateStyleRequest request);
    Task<bool> DeleteAsync(int id);
}
