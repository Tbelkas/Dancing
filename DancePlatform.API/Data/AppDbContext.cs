using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<User> Users => Set<User>();
    public DbSet<Dance> Dances => Set<Dance>();
    public DbSet<Style> Styles => Set<Style>();
    public DbSet<MusicalStyle> MusicalStyles => Set<MusicalStyle>();
    public DbSet<Video> Videos => Set<Video>();
    public DbSet<DanceStyle> DanceStyles => Set<DanceStyle>();
    public DbSet<DanceMusicalStyle> DanceMusicalStyles => Set<DanceMusicalStyle>();
    public DbSet<UserFavoriteDance> UserFavoriteDances => Set<UserFavoriteDance>();
    public DbSet<UserLearnedDance> UserLearnedDances => Set<UserLearnedDance>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<DanceStyle>()
            .HasKey(ds => new { ds.DanceId, ds.StyleId });

        modelBuilder.Entity<DanceStyle>()
            .HasOne(ds => ds.Dance)
            .WithMany(d => d.DanceStyles)
            .HasForeignKey(ds => ds.DanceId);

        modelBuilder.Entity<DanceStyle>()
            .HasOne(ds => ds.Style)
            .WithMany(s => s.DanceStyles)
            .HasForeignKey(ds => ds.StyleId);

        modelBuilder.Entity<DanceMusicalStyle>()
            .HasKey(dms => new { dms.DanceId, dms.MusicalStyleId });

        modelBuilder.Entity<DanceMusicalStyle>()
            .HasOne(dms => dms.Dance)
            .WithMany(d => d.DanceMusicalStyles)
            .HasForeignKey(dms => dms.DanceId);

        modelBuilder.Entity<DanceMusicalStyle>()
            .HasOne(dms => dms.MusicalStyle)
            .WithMany(ms => ms.DanceMusicalStyles)
            .HasForeignKey(dms => dms.MusicalStyleId);

        modelBuilder.Entity<UserFavoriteDance>()
            .HasKey(ufd => new { ufd.UserId, ufd.DanceId });

        modelBuilder.Entity<UserFavoriteDance>()
            .HasOne(ufd => ufd.User)
            .WithMany(u => u.FavoriteDances)
            .HasForeignKey(ufd => ufd.UserId);

        modelBuilder.Entity<UserFavoriteDance>()
            .HasOne(ufd => ufd.Dance)
            .WithMany(d => d.FavoritedBy)
            .HasForeignKey(ufd => ufd.DanceId);

        modelBuilder.Entity<UserLearnedDance>()
            .HasKey(uld => new { uld.UserId, uld.DanceId });

        modelBuilder.Entity<UserLearnedDance>()
            .HasOne(uld => uld.User)
            .WithMany(u => u.LearnedDances)
            .HasForeignKey(uld => uld.UserId);

        modelBuilder.Entity<UserLearnedDance>()
            .HasOne(uld => uld.Dance)
            .WithMany(d => d.LearnedBy)
            .HasForeignKey(uld => uld.DanceId);

        modelBuilder.Entity<User>()
            .HasIndex(u => u.Username)
            .IsUnique();
    }
}
