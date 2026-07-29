using System.Text;
using DancePlatform.API.Data;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.ResponseCompression;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
// Apache proxies to Kestrel over plain HTTP and passes upstream Content-Encoding through,
// so compressing here is what the browser ends up receiving.
builder.Services.AddResponseCompression(options =>
{
    options.EnableForHttps = true;
    options.Providers.Add<BrotliCompressionProvider>();
    options.Providers.Add<GzipCompressionProvider>();
});
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.AddProblemDetails();
// Backs the short-lived catalog-size cache in DanceService (see the "dances:grandTotal" key) so
// the "N of M dances" figure isn't a full COUNT(*) on every keystroke.
builder.Services.AddMemoryCache();

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("Default")));

builder.Services.AddScoped<IAuthService, AuthService>();
builder.Services.AddScoped<IDanceService, DanceService>();
builder.Services.AddScoped<IStyleService, StyleService>();
builder.Services.AddScoped<IMusicalStyleService, MusicalStyleService>();
builder.Services.AddScoped<IVideoService, VideoService>();
builder.Services.AddScoped<IUserVideoLoopService, UserVideoLoopService>();
builder.Services.AddScoped<IVideoNoteService, VideoNoteService>();
builder.Services.AddScoped<IChoreoService, ChoreoService>();
builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddScoped<IPracticeService, PracticeService>();
builder.Services.AddScoped<IInstructorService, InstructorService>();
builder.Services.AddScoped<IRoadmapService, RoadmapService>();
builder.Services.AddScoped<IImportService, ImportService>();

// Reads a YouTube video's own chapters when a clip is added. Short timeout and a browser-ish
// UA: the watch page is the only place chapters are published, and a slow lookup must not
// hold up the form. The consent cookies keep EU requests off the interstitial page.
builder.Services.AddHttpClient<IYoutubeChapterService, YoutubeChapterService>(client =>
{
    client.BaseAddress = new Uri("https://www.youtube.com");
    client.Timeout = TimeSpan.FromSeconds(10);
    client.DefaultRequestHeaders.Add("User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36");
    client.DefaultRequestHeaders.Add("Accept-Language", "en-US,en;q=0.9");
    client.DefaultRequestHeaders.Add("Cookie", "CONSENT=YES+cb; SOCS=CAI");
});

builder.Services.AddHttpClient<IOllamaService, OllamaService>(client =>
{
    var baseUrl = builder.Configuration["Ollama:BaseUrl"] ?? "http://localhost:11434";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromSeconds(120);
});

var jwtKey = builder.Configuration["Jwt:Key"];
// Refuse to boot a non-Development environment with a missing or insecure signing key —
// the committed default is a dev-only placeholder; prod must supply a strong Jwt__Key.
if (string.IsNullOrWhiteSpace(jwtKey) ||
    (!builder.Environment.IsDevelopment() && (jwtKey.Length < 32 || jwtKey.Contains("dev-insecure", StringComparison.Ordinal))))
{
    throw new InvalidOperationException(
        "Jwt:Key is missing or insecure. Set a strong Jwt__Key (>= 32 chars) via environment configuration before running outside Development.");
}
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"],
            ValidAudience = builder.Configuration["Jwt:Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey))
        };
    });

builder.Services.AddCors(options =>
    options.AddDefaultPolicy(policy =>
        policy.WithOrigins(builder.Configuration["Cors:Origin"] ?? "http://localhost:4200")
              .AllowAnyHeader()
              .AllowAnyMethod()));

var app = builder.Build();

// Unhandled exceptions become RFC-7807 ProblemDetails instead of leaking stack traces.
app.UseExceptionHandler();

app.UseResponseCompression();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    await db.Database.MigrateAsync();
    await SeedData.SeedAsync(db);
    // Roadmaps are authored content, so this runs every boot (not only on an empty DB) — it
    // re-syncs edited paths and re-links steps to moves that have since been added.
    await RoadmapSeeder.SeedAsync(
        db,
        app.Environment.ContentRootPath,
        scope.ServiceProvider.GetRequiredService<ILoggerFactory>().CreateLogger(nameof(RoadmapSeeder)));
}

app.Run();
