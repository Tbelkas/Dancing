using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddVideoDurationSeconds : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "DurationSeconds",
                table: "Videos",
                type: "integer",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "DurationSeconds",
                table: "Videos");
        }
    }
}
