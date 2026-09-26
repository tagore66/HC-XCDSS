import DoctorDirectory from "./DoctorDirectory";

export default function ProfessionalSelector({ selectedProfessional, onSelectProfessional, onContinue }) {
  return (
    <div className="professional-selector-wrapper">
      <DoctorDirectory
        selectedProfessional={selectedProfessional}
        onSelectProfessional={onSelectProfessional}
        onContinue={onContinue}
        showPoolOption={true}
        showHeader={true}
      />
    </div>
  );
}
