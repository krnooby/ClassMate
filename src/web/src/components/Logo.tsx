/**
 * ClassMate Logo Component
 * 브랜딩 로고 컴포넌트
 */

interface LogoProps {
  variant?: 'full' | 'simple' | 'icon';
  className?: string;
}

export default function Logo({ variant = 'simple', className = '' }: LogoProps) {
  if (variant === 'icon') {
    return (
      <div className={`flex items-center ${className}`}>
        <img
          src="/logo2.png"
          alt="ClassMate Logo"
          className="h-40 w-auto object-contain"
          style={{ mixBlendMode: 'multiply' }}
        />
      </div>
    );
  }

  if (variant === 'full') {
    return (
      <div className={`flex items-center ${className}`}>
        <img
          src="/logo2.png"
          alt="ClassMate"
          className="h-48 w-auto object-contain"
          style={{ mixBlendMode: 'multiply' }}
        />
      </div>
    );
  }

  // Simple variant (네비게이션바용)
  return (
    <div className={`flex items-center ${className}`}>
      <img
        src="/logo2.png"
        alt="ClassMate"
        className="h-40 w-auto object-contain"
        style={{ mixBlendMode: 'multiply' }}
      />
    </div>
  );
}
