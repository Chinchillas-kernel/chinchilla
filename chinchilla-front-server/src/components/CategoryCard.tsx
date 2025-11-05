import { LucideIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface CategoryCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  route: string;
}

const CategoryCard = ({ icon: Icon, title, description, route }: CategoryCardProps) => {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate(route)}
      className="group relative flex w-full flex-col items-center gap-4 rounded-2xl border border-border bg-card p-6 text-center transition-all hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5"
    >
      <div className="rounded-full bg-accent p-4 transition-colors group-hover:bg-primary/10">
        <Icon className="h-8 w-8 text-accent-foreground transition-colors group-hover:text-primary" />
      </div>
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-card-foreground">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </button>
  );
};

export default CategoryCard;
