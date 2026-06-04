using DancePlatform.API.DTOs.Instructor;
using DancePlatform.API.Filters;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class InstructorsController : ControllerBase
{
    private readonly IInstructorService _instructorService;

    public InstructorsController(IInstructorService instructorService) => _instructorService = instructorService;

    [HttpGet]
    public async Task<IActionResult> GetAll() =>
        Ok(await _instructorService.GetAllAsync());

    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        var instructor = await _instructorService.GetByIdAsync(id);
        return instructor is null ? NotFound() : Ok(instructor);
    }

    [RequireAdmin]
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateInstructorRequest request)
    {
        var instructor = await _instructorService.CreateAsync(request);
        return CreatedAtAction(nameof(GetById), new { id = instructor.Id }, instructor);
    }

    [RequireAdmin]
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _instructorService.DeleteAsync(id);
        return deleted ? NoContent() : NotFound();
    }
}
