import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";

interface JobProfileData {
  age: string;
  gender: string;
  region: string;
}

interface LegalProfileData {
  age?: string;
  gender?: string;
  income?: string;
  interests?: string[];
}

interface ProfileFormProps {
  category: "job" | "legal";
  onComplete: (data: JobProfileData | LegalProfileData) => void;
}

const ProfileForm = ({ category, onComplete }: ProfileFormProps) => {
  const [jobProfile, setJobProfile] = useState<JobProfileData>({
    age: "",
    gender: "",
    region: "",
  });

  const [legalProfile, setLegalProfile] = useState<LegalProfileData>({
    age: "",
    gender: "",
    income: "",
    interests: [],
  });

  const legalInterestOptions = [
    { id: "inheritance", label: "상속/증여" },
    { id: "realestate", label: "부동산" },
    { id: "finance", label: "금융" },
    { id: "income", label: "월소득" },
  ];

  const handleJobSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (jobProfile.age && jobProfile.gender && jobProfile.region) {
      onComplete(jobProfile);
    }
  };

  const handleLegalSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onComplete(legalProfile);
  };

  const toggleInterest = (interestId: string) => {
    setLegalProfile((prev) => {
      const currentInterests = prev.interests || [];
      const newInterests = currentInterests.includes(interestId)
        ? currentInterests.filter((id) => id !== interestId)
        : [...currentInterests, interestId];
      return { ...prev, interests: newInterests };
    });
  };

  if (category === "job") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <div className="rounded-2xl border bg-card p-8 shadow-sm">
          <h2 className="mb-6 text-2xl font-semibold text-card-foreground">
            일자리 매칭을 위한 프로필 입력
          </h2>
          <p className="mb-6 text-sm text-muted-foreground">
            더 정확한 일자리 매칭을 위해 기본 정보를 입력해주세요. 모든 항목은 필수입니다.
          </p>

          <form onSubmit={handleJobSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="age" className="text-sm font-medium">
                나이 <span className="text-destructive">*</span>
              </Label>
              <Input
                id="age"
                type="number"
                placeholder="예: 65"
                value={jobProfile.age}
                onChange={(e) => setJobProfile({ ...jobProfile, age: e.target.value })}
                required
                min="1"
                max="120"
                className="bg-background"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium">
                성별 <span className="text-destructive">*</span>
              </Label>
              <RadioGroup
                value={jobProfile.gender}
                onValueChange={(value) => setJobProfile({ ...jobProfile, gender: value })}
                required
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="male" id="male" />
                  <Label htmlFor="male" className="font-normal">남성</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="female" id="female" />
                  <Label htmlFor="female" className="font-normal">여성</Label>
                </div>
              </RadioGroup>
            </div>

            <div className="space-y-2">
              <Label htmlFor="region" className="text-sm font-medium">
                거주 지역 <span className="text-destructive">*</span>
              </Label>
              <Select
                value={jobProfile.region}
                onValueChange={(value) => setJobProfile({ ...jobProfile, region: value })}
                required
              >
                <SelectTrigger className="bg-background">
                  <SelectValue placeholder="지역을 선택하세요" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="서울">서울</SelectItem>
                  <SelectItem value="부산">부산</SelectItem>
                  <SelectItem value="대구">대구</SelectItem>
                  <SelectItem value="인천">인천</SelectItem>
                  <SelectItem value="광주">광주</SelectItem>
                  <SelectItem value="대전">대전</SelectItem>
                  <SelectItem value="울산">울산</SelectItem>
                  <SelectItem value="세종">세종</SelectItem>
                  <SelectItem value="경기">경기</SelectItem>
                  <SelectItem value="강원">강원</SelectItem>
                  <SelectItem value="충북">충북</SelectItem>
                  <SelectItem value="충남">충남</SelectItem>
                  <SelectItem value="전북">전북</SelectItem>
                  <SelectItem value="전남">전남</SelectItem>
                  <SelectItem value="경북">경북</SelectItem>
                  <SelectItem value="경남">경남</SelectItem>
                  <SelectItem value="제주">제주</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={!jobProfile.age || !jobProfile.gender || !jobProfile.region}
            >
              일자리 상담 시작하기
            </Button>
          </form>
        </div>
      </div>
    );
  }

  if (category === "legal") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <div className="rounded-2xl border bg-card p-8 shadow-sm">
          <h2 className="mb-6 text-2xl font-semibold text-card-foreground">
            법률 상담을 위한 정보 입력
          </h2>
          <p className="mb-6 text-sm text-muted-foreground">
            더 정확한 법률 상담을 위해 정보를 입력해주세요. 모든 항목은 선택사항입니다.
          </p>

          <form onSubmit={handleLegalSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="legal-age" className="text-sm font-medium">
                나이 (선택사항)
              </Label>
              <Input
                id="legal-age"
                type="number"
                placeholder="예: 65"
                value={legalProfile.age}
                onChange={(e) => setLegalProfile({ ...legalProfile, age: e.target.value })}
                min="1"
                max="120"
                className="bg-background"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium">성별 (선택사항)</Label>
              <RadioGroup
                value={legalProfile.gender}
                onValueChange={(value) => setLegalProfile({ ...legalProfile, gender: value })}
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="male" id="legal-male" />
                  <Label htmlFor="legal-male" className="font-normal">남성</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="female" id="legal-female" />
                  <Label htmlFor="legal-female" className="font-normal">여성</Label>
                </div>
              </RadioGroup>
            </div>

            <div className="space-y-2">
              <Label htmlFor="income" className="text-sm font-medium">
                소득 (선택사항)
              </Label>
              <Select
                value={legalProfile.income}
                onValueChange={(value) => setLegalProfile({ ...legalProfile, income: value })}
              >
                <SelectTrigger className="bg-background">
                  <SelectValue placeholder="소득 구간을 선택하세요" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="under-100">100만원 미만</SelectItem>
                  <SelectItem value="100-200">100만원 ~ 200만원</SelectItem>
                  <SelectItem value="200-300">200만원 ~ 300만원</SelectItem>
                  <SelectItem value="300-500">300만원 ~ 500만원</SelectItem>
                  <SelectItem value="over-500">500만원 이상</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-3">
              <Label className="text-sm font-medium">관심 분야 (선택사항)</Label>
              <div className="space-y-2">
                {legalInterestOptions.map((option) => (
                  <div key={option.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={option.id}
                      checked={legalProfile.interests?.includes(option.id)}
                      onCheckedChange={() => toggleInterest(option.id)}
                    />
                    <Label htmlFor={option.id} className="font-normal cursor-pointer">
                      {option.label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
              <Button
                type="button"
                variant="outline"
                className="sm:w-auto"
                onClick={() => onComplete({})}
              >
                건너뛰기
              </Button>
              <Button type="submit" className="sm:w-auto px-6">
                법률 상담 시작하기
              </Button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return null;
};

export default ProfileForm;
