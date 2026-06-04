using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddVideoStartEndTime2 : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "StartTime",
                table: "Videos",
                type: "integer",
                nullable: true);

            migrationBuilder.AddColumn<int>(
                name: "EndTime",
                table: "Videos",
                type: "integer",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(name: "EndTime", table: "Videos");
            migrationBuilder.DropColumn(name: "StartTime", table: "Videos");
        }
    }
}
