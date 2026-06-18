using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddDenormalizedDanceCounts : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<double>(
                name: "AverageRating",
                table: "Dances",
                type: "double precision",
                nullable: false,
                defaultValue: 0.0);

            migrationBuilder.AddColumn<int>(
                name: "FavoriteCount",
                table: "Dances",
                type: "integer",
                nullable: false,
                defaultValue: 0);

            migrationBuilder.AddColumn<int>(
                name: "LearnedCount",
                table: "Dances",
                type: "integer",
                nullable: false,
                defaultValue: 0);

            migrationBuilder.AddColumn<int>(
                name: "RatingCount",
                table: "Dances",
                type: "integer",
                nullable: false,
                defaultValue: 0);

            // Backfill counts from existing data
            migrationBuilder.Sql(@"
                UPDATE ""Dances"" d
                SET ""FavoriteCount"" = (SELECT COUNT(*) FROM ""UserFavoriteDances"" WHERE ""DanceId"" = d.""Id"");

                UPDATE ""Dances"" d
                SET ""LearnedCount"" = (SELECT COUNT(*) FROM ""UserLearnedDances"" WHERE ""DanceId"" = d.""Id"");

                UPDATE ""Dances"" d
                SET ""RatingCount"" = (SELECT COUNT(*) FROM ""DanceRatings"" WHERE ""DanceId"" = d.""Id""),
                    ""AverageRating"" = COALESCE(
                        (SELECT AVG(""Rating"") FROM ""DanceRatings"" WHERE ""DanceId"" = d.""Id""), 0);
            ");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "AverageRating",
                table: "Dances");

            migrationBuilder.DropColumn(
                name: "FavoriteCount",
                table: "Dances");

            migrationBuilder.DropColumn(
                name: "LearnedCount",
                table: "Dances");

            migrationBuilder.DropColumn(
                name: "RatingCount",
                table: "Dances");
        }
    }
}
